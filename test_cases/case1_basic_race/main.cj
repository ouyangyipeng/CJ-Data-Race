// 测试用例1: 基本数据竞争
// 两个线程同时写入共享变量，无同步保护

main() {
    var counter: Int64 = 0
    
    // spawn创建线程1
    spawn {
        counter = counter + 1  // 写操作，第7行
    }
    
    // spawn创建线程2
    spawn {
        counter = counter + 1  // 写操作，第12行
    }
    
    println(counter)
}