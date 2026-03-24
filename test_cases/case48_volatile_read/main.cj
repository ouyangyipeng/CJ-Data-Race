// case48: volatile变量测试
// 测试volatile关键字的使用

main() {
    @Volatile
    var flag: Bool = false
    var data: Int64 = 0
    
    spawn {
        data = 100
        flag = true  // volatile写
    }
    
    spawn {
        while (!flag) {  // volatile读
            // 等待
        }
        let value = data  // 读取data
    }
}