// 测试用例16: 多文件项目
// 测试跨文件的数据竞争检测

// 引用另一个文件的变量
extern var globalCounter: Int64

main() {
    // 线程1: 写入
    spawn {
        globalCounter = globalCounter + 1
    }
    
    // 线程2: 写入
    spawn {
        globalCounter = globalCounter + 1
    }
    
    println(globalCounter)
}