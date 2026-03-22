// 测试用例2: 读写竞争
// 一个线程读，另一个线程写

main() {
    var data: Int64 = 100
    var result: Int64 = 0
    
    // 线程1: 读取data
    spawn {
        result = data  // 读操作，第8行
    }
    
    // 线程2: 写入data
    spawn {
        data = 200  // 写操作，第13行
    }
    
    println(result)
}